#!/usr/bin/env python3
"""CLI entry point for the OpenStartup API server.

Usage:
    python run_server.py                # Default: mock mode, port 8000
    python run_server.py --port 9000    # Custom port
    python run_server.py --reload       # Development with auto-reload
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src/ directory to path so 'openteam.server' package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenStartup API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock", help="Server mode")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--real-sessions",
        type=str,
        default=None,
        metavar="DIR",
        help="Enable persistent sessions from DIR (runtime root, default: mock fixture data)",
    )
    parser.add_argument(
        "--resume-server",
        type=str,
        default=None,
        metavar="NAME",
        help='Resume a specific server dir (e.g., server_20260406_...). Use "new" to force a new server.',
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    import uvicorn
    from openteam.server.main import app

    app.state.mode = args.mode

    if args.real_sessions:
        app.state.real_sessions_dir = str(Path(args.real_sessions).expanduser())
    if args.resume_server:
        app.state.resume_server = args.resume_server

    print(f"Starting OpenStartup API Server ({args.mode} mode)")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Debug: {args.debug}")
    print(f"  Reload: {args.reload}")
    if args.real_sessions:
        print(f"  Runtime Root: {app.state.real_sessions_dir}")
    if args.resume_server:
        print(f"  Resume Server: {args.resume_server}")
    print()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
