#!/usr/bin/env bash
# Submit the hack SFT workflow to ML Studio.
#
# What this script does:
#   1. (Optional) Validate the workflow descriptor — surfaces YAML/schema errors
#      WITHOUT submitting and WITHOUT consuming compute.
#   2. Submit the run via `atlas ml workflow run` (uses staging by default for
#      first-time hack; switch to `prod` once verified).
#   3. Capture the run-id and write it to artifacts/last_run_id.txt for the
#      monitor script.
#
# Verified against:
#   atlas ml workflow run/submit/validate (CLI v0.x — see `atlas ml workflow --help`)
#   ml-studio-docs/.../workflows/programmatic-triggering/index.md
#
# Auth:
#   `atlas ml workflow` uses your atlas SSO + slauth in the background.
#   No YubiKey required. If you get 401, run `atlas auth login`.
#
# Usage:
#   bash 02-submit-job.sh                 # validate + submit to staging
#   ENV=prod bash 02-submit-job.sh        # submit to prod
#   DRY_RUN=true bash 02-submit-job.sh    # only validate, do not run
#   OPEN_URL=true bash 02-submit-job.sh   # also open the run page in browser

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DESCRIPTOR="${ROOT_DIR}/configs/hack_oss_20b_sft.yaml"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${ARTIFACTS_DIR}" "${LOG_DIR}"

ENV="${ENV:-staging}"
DRY_RUN="${DRY_RUN:-false}"
OPEN_URL="${OPEN_URL:-false}"

cyan()  { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }

cyan "============================================================"
cyan " ML Studio Hack Submit"
cyan "============================================================"
echo "Descriptor : ${DESCRIPTOR}"
echo "Env        : ${ENV}"
echo "Dry-run    : ${DRY_RUN}"
echo

# ---- Pre-flight ----------------------------------------------------------
if [[ ! -f "${DESCRIPTOR}" ]]; then
  red "❌ Descriptor not found: ${DESCRIPTOR}"
  exit 1
fi

if ! command -v atlas >/dev/null 2>&1; then
  red "❌ 'atlas' CLI not found on PATH. See https://developer.atlassian.com/platform/atlas-cli/users/install/"
  exit 1
fi

# ---- Step 1: Validate ---------------------------------------------------
cyan ">> Validating workflow descriptor (no compute used)..."
VALIDATE_LOG="${LOG_DIR}/validate-$(date +%Y%m%d-%H%M%S).log"
if atlas ml workflow validate -d "${DESCRIPTOR}" -e "${ENV}" 2>&1 | tee "${VALIDATE_LOG}"; then
  green "✓ Validation passed"
else
  red "❌ Validation failed — see ${VALIDATE_LOG}"
  exit 2
fi

if [[ "${DRY_RUN}" == "true" ]]; then
  cyan "DRY_RUN=true — stopping after validation."
  exit 0
fi

# ---- Step 2: Submit run -------------------------------------------------
cyan ">> Submitting run to ${ENV}..."
RUN_LOG="${LOG_DIR}/run-$(date +%Y%m%d-%H%M%S).log"
RUN_ARGS=( -d "${DESCRIPTOR}" -e "${ENV}" --json )
[[ "${OPEN_URL}" == "true" ]] && RUN_ARGS+=( --open-url )

# Capture both stdout (json) and stderr (atlas chatter) but separate them
if ! atlas ml workflow run "${RUN_ARGS[@]}" > "${RUN_LOG}.stdout" 2> "${RUN_LOG}.stderr"; then
  red "❌ Submission failed."
  echo "------ stderr ------"
  cat "${RUN_LOG}.stderr"
  echo "------ stdout ------"
  cat "${RUN_LOG}.stdout"
  exit 3
fi

# Pretty-print the JSON response
green "✓ Submitted!"
echo "Response:"
cat "${RUN_LOG}.stdout"
echo

# Try to extract run_id (jq if available, else grep)
RUN_ID=""
if command -v jq >/dev/null 2>&1; then
  RUN_ID=$(jq -r '.run_id // .id // .runId // empty' < "${RUN_LOG}.stdout" || true)
fi
if [[ -z "${RUN_ID}" ]]; then
  RUN_ID=$(grep -oE '"(run_?[Ii]d|id)"\s*:\s*"[^"]+"' "${RUN_LOG}.stdout" | head -1 | sed -E 's/.*"([^"]+)"$/\1/' || true)
fi

if [[ -n "${RUN_ID}" ]]; then
  echo "${RUN_ID}" > "${ARTIFACTS_DIR}/last_run_id.txt"
  echo "${ENV}"    > "${ARTIFACTS_DIR}/last_env.txt"
  green "✓ Run ID saved to ${ARTIFACTS_DIR}/last_run_id.txt"
  echo "Run ID: ${RUN_ID}"
  echo
  echo "Monitor with:"
  echo "  bash ${ROOT_DIR}/scripts/03-monitor-run.sh"
else
  cyan "⚠️  Could not parse run_id from response — monitor manually:"
  echo "  atlas ml workflow run-status -e ${ENV} -r <RUN_ID>"
fi
