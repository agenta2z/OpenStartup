"""Shared parser: CLI-style argument strings → canonical `arguments` dict.

A tool's ``arguments`` reaches an executor as a dict whose keys are ALWAYS
underscored (Option D convention). Two callers feed that dict:

* the **user slash-command** path (``manager_websocket_routes``) — a user types
  ``/understand_codebase /path --template-version modeling``;
* the **agent action** path (``ToolDispatcher``) — the LLM emits a
  ``ToolsToInvoke`` action whose ``arguments`` is *usually* a dict, but is
  sometimes a CLI-style string mirroring the tool's own usage examples
  (the rendered tool docs show ``understand-codebase /path/to/model.py``), e.g.
  ``{"name": "understand_codebase", "arguments": "/path --template-version modeling"}``.

Both must accept the string form, so the parser lives here as the single source
of truth. ``coerce_tool_arguments`` is the boundary helper the dispatcher uses
to normalize whatever shape the LLM produced into the dict every executor
expects (mirrors the existing str/list/dict coercion done for slash commands in
``commands.dispatch_as_tool``).
"""

from __future__ import annotations

import shlex
from typing import Any

# Keys that may repeat and accumulate into a list (e.g. --override a --override b).
_REPEATABLE_KEYS = {"override"}


def parse_cli_args(args_str: str, bool_flags: "set[str]" = frozenset()) -> dict[str, Any]:
    """Parse ``--key value`` pairs + bare ``--flag`` + positional ``request``.

    Rules:
      - known bool-flag → ``{key: True}``, advance 1
      - next token starts with ``--`` → bare flag, advance 1
      - otherwise consume next token as the value
    Repeated keys in ``_REPEATABLE_KEYS`` accumulate into a list. All unconsumed
    non-flag tokens become the positional ``request`` (joined by space). Dash-form
    keys are normalized to underscores so dict keys are uniformly underscored.
    """
    result: dict[str, Any] = {}
    try:
        parts = shlex.split(args_str, posix=True)
    except ValueError:
        parts = args_str.split()
    consumed: set[int] = set()
    i = 0
    while i < len(parts):
        if parts[i].startswith("--"):
            key = parts[i].lstrip("-").replace("-", "_")
            if key in bool_flags or i + 1 >= len(parts) or parts[i + 1].startswith("--"):
                result[key] = True
                consumed.add(i)
                i += 1
            else:
                val = parts[i + 1]
                if key in _REPEATABLE_KEYS:
                    result.setdefault(key, []).append(val)
                else:
                    result[key] = val
                consumed.update({i, i + 1})
                i += 2
        else:
            i += 1
    positional = [
        parts[j]
        for j in range(len(parts))
        if j not in consumed and not parts[j].startswith("--")
    ]
    if positional:
        result.setdefault("request", " ".join(positional))
    return result


def bool_flags_for_tool(tool_def: Any) -> "frozenset[str]":
    """Derive the value-less (boolean) flag names from a tool's parameters.

    Without this, the parser would swallow the token after a bare ``--flag`` as
    that flag's value (e.g. ``--plan "do X"`` → ``{plan: "do X"}`` instead of
    ``{plan: True, request: "do X"}``). Returns underscored names.
    """
    flags: set[str] = set()
    for p in getattr(tool_def, "parameters", None) or []:
        ptype = getattr(p, "type", None)
        name = getattr(p, "name", None)
        if ptype is None and isinstance(p, dict):
            ptype, name = p.get("type"), p.get("name")
        if ptype == "flag" and name:
            flags.add(str(name).lstrip("-").replace("-", "_"))
    return frozenset(flags)


def coerce_tool_arguments(arguments: Any, tool_def: Any = None) -> dict[str, Any]:
    """Normalize a tool's ``arguments`` into the canonical dict form.

    - ``dict`` → returned unchanged (the documented, common case).
    - ``str``  → parsed as a CLI-style invocation (positional → ``request``).
    - ``list``/``tuple`` → first string element parsed as a CLI string (the LLM
      occasionally wraps the args in a list); otherwise ``{}``.
    - anything else (incl. ``None``) → ``{}``.
    """
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        return parse_cli_args(arguments, bool_flags_for_tool(tool_def))
    if isinstance(arguments, (list, tuple)):
        if arguments and isinstance(arguments[0], str):
            return parse_cli_args(arguments[0], bool_flags_for_tool(tool_def))
        return {}
    return {}
