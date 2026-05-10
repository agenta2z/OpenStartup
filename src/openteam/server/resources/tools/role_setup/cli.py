"""Standalone CLI for the role_setup tool."""
from pathlib import Path
from openteam.server.services.tool_cli import run_cli
from .executor import execute

_TOOL_JSON = Path(__file__).parent / "tool.json"

def main(argv=None) -> int:
    return run_cli(_TOOL_JSON, execute, argv=argv)

if __name__ == "__main__":
    raise SystemExit(main())
