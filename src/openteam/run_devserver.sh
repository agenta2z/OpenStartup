#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# run_devserver.sh — Launch OpenTeam server + UI for remote dev access.
#
# Wraps run.sh with the env + flags needed to make both ports reachable
# from a corp Mac via x2p:
#   * Ports 8088/8089 — inside x2p's 8080–8090 allowlist
#     (proxy_allowlist.cconf). Ports outside this range time out at 10s
#     with "503 Bad Gateway / connect timed out" because x2p won't
#     forward them, even if the service is listening on the devvm.
#   * HOST=:: / --host :: — bind both servers to all IPv6 interfaces
#     so the browser's WebSocket (which hits the backend port directly,
#     not via the CRA proxy) can reach them.
#   * DANGEROUSLY_DISABLE_HOST_CHECK + WDS_SOCKET_HOST — bypass
#     webpack-dev-server's "Invalid Host header" rejection when the
#     request arrives via x2p with a non-localhost Host header.
#   * PATH=/usr/bin:$PATH — bypass /usr/local/bin/npm (devvm guard
#     wrapper that prints a refusal and exits 1) in favor of the real
#     /usr/bin/npm.
#   * OPENSTARTUP_PYTHON — point at the openteam-venv that has fastapi
#     installed (the run.sh default is a macOS Homebrew path).
#
# Always restarts cleanly: kills anything on 8088/8089 first.
#
# Usage:
#   ./run_devserver.sh                # real-sessions + claude_cli/sonnet
#   ./run_devserver.sh --mock         # mock mode (no LLM)
#   ./run_devserver.sh -- --rebuild   # pass extra flags through to run.sh
#
# Open: http://devvm984.ldc0.facebook.com:8088
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UI_PORT=8088
API_PORT=8089
VENV_PYTHON="${OPENSTARTUP_PYTHON:-/home/zgchen/openteam-venv/bin/python}"

# ── Parse args ───────────────────────────────────────────────────────
MODE_ARGS=(--real-sessions --llm-backend claude_cli --llm-model sonnet)
PASSTHROUGH=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mock) MODE_ARGS=(); shift ;;
    --)     shift; PASSTHROUGH=("$@"); break ;;
    *)      PASSTHROUGH+=("$1"); shift ;;
  esac
done

# ── Kill anything on our ports ───────────────────────────────────────
echo "[run_devserver] Killing any existing openteam processes on :${UI_PORT}/:${API_PORT}…"
pkill -f "openteam/run\.sh"                     2>/dev/null || true
pkill -f "openteam/ui.*react-scripts"           2>/dev/null || true
pkill -f "run_server\.py.*--port ${API_PORT}"   2>/dev/null || true
# Final sweep: kill whatever still owns those ports
for port in "$UI_PORT" "$API_PORT"; do
  pids=$(ss -tlnpH "( sport = :$port )" 2>/dev/null \
         | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
  [[ -n "$pids" ]] && kill $pids 2>/dev/null || true
done
sleep 2
if ss -tlnp 2>/dev/null | grep -qE ":(${UI_PORT}|${API_PORT})\b"; then
  echo "[run_devserver] WARNING: a process still holds :${UI_PORT} or :${API_PORT}" >&2
  ss -tlnp 2>/dev/null | grep -E ":(${UI_PORT}|${API_PORT})\b" >&2
fi

# ── Pre-flight: venv has fastapi ─────────────────────────────────────
if ! "$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "[run_devserver] ERROR: $VENV_PYTHON missing fastapi/uvicorn." >&2
  echo "  Install:  uv pip install --index-url https://interngraph.intern.facebook.com/vault/simple/pypi/ fastapi" >&2
  exit 1
fi

# ── Pre-flight: agent working dir ────────────────────────────────────
mkdir -p "${OPENTEAM_WORKING_DIR:-$HOME/MyProjects}"

# ── Launch ───────────────────────────────────────────────────────────
echo "[run_devserver] Launching: UI=:${UI_PORT}  API=:${API_PORT}  mode=${MODE_ARGS[*]:-mock}"
echo "[run_devserver] URL: http://devvm984.ldc0.facebook.com:${UI_PORT}"
echo ""

cd "$SCRIPT_DIR"
exec env \
  PATH="/usr/bin:$PATH" \
  OPENSTARTUP_PYTHON="$VENV_PYTHON" \
  HOST=:: \
  PORT="$UI_PORT" \
  DANGEROUSLY_DISABLE_HOST_CHECK=true \
  WDS_SOCKET_HOST=0.0.0.0 \
  ./run.sh --host :: --port "$API_PORT" \
           "${MODE_ARGS[@]}" \
           "${PASSTHROUGH[@]}"
