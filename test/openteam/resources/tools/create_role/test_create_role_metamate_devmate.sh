#!/usr/bin/env bash
# ----------------------------------------------------------------------
# test_create_role_metamate_devmate.sh
#
# Run create_role with the Metamate/Devmate inferencer overrides via
# `test_create_role_metamate_devmate.py`. This script:
#   1. Activates the project venv (/home/zgchen/openteam-venv)
#   2. Sets PYTHONPATH to include OpenStartup + AgentFoundation + RichPythonUtils
#   3. Invokes the driver with default --mode=devmate_only (--max-facets 2)
#
# Usage:
#   ./test_create_role_metamate_devmate.sh "hire a machine learning engineer (MLE)"
#   ./test_create_role_metamate_devmate.sh --mode metamate_and_devmate "..."
#   ./test_create_role_metamate_devmate.sh --mode rovochat_and_devmate "..."
#   ./test_create_role_metamate_devmate.sh --max-facets 3 "..."
#
# Why a separate driver/script (vs editing create_role_bta.yaml in place)?
#   The override mechanism (_run_topology's `overrides` dict) lets us swap
#   _params.default_*_inferencer at runtime, so the canonical YAML stays
#   untouched. Compare to test_create_role.sh which runs the YAML as-is
#   with RovoChat/RovoDevCLI.
#
# Runtime gotchas:
#   * devmate_only mode    — runs fully here (devmate binary at /usr/local/bin/devmate)
#   * metamate_* mode      — needs Buck (msl.metamate.cli.metamate_graphql); will
#                            raise RuntimeError("MetaMate upstream client not available")
#                            in pure venv. See the .py docstring for details.
# ----------------------------------------------------------------------
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
readonly VENV="${OPENTEAM_VENV:-/home/zgchen/openteam-venv}"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly LOG_FILE="${REPO_ROOT}/create_role_metamate_devmate_${TIMESTAMP}.log"

if [ ! -x "${VENV}/bin/python" ]; then
    echo "[ERROR] Python venv not found at ${VENV}." >&2
    echo "         Bootstrap it with:" >&2
    echo "         uv venv --python /usr/local/fbcode/platform010-compat/bin/python3.12 ${VENV}" >&2
    echo "         source ${VENV}/bin/activate" >&2
    echo "         uv pip install attrs omegaconf jinja2 pyyaml pydantic hydra-core \\" >&2
    echo "             python-dotenv typer fastmcp mcp websockets requests httpx \\" >&2
    echo "             pyre-extensions beautifulsoup4 boto3 botocore" >&2
    exit 1
fi

# Activate venv + set PYTHONPATH (mirrors test_create_role.sh's discovery)
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

CORE_PROJECTS="$(cd "${REPO_ROOT}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}/src:${CORE_PROJECTS}/AgentFoundation/src:${CORE_PROJECTS}/RichPythonUtils/src${PYTHONPATH:+:$PYTHONPATH}"

echo "[INFO]  Repo root:     ${REPO_ROOT}"
echo "[INFO]  Venv:          ${VENV}"
echo "[INFO]  Python:        $(python --version 2>&1)"
echo "[INFO]  PYTHONPATH:    ${PYTHONPATH}"
echo "[INFO]  Log file:      ${LOG_FILE}"
echo "[INFO]  Workspace:     ${REPO_ROOT}/_runtime/tasks/create_role/create_role_<TS>_<UUID>/"
echo

cd "${REPO_ROOT}"
python -m test.openteam.resources.tools.create_role.test_create_role_metamate_devmate "$@" 2>&1 | tee "${LOG_FILE}"
