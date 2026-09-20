#!/usr/bin/env bash
# Poll the status of the most recent ML Studio workflow run.
#
# Reads run-id from artifacts/last_run_id.txt (written by 02-submit-job.sh),
# or accepts RUN_ID=... env override.
#
# Usage:
#   bash 03-monitor-run.sh                           # uses last_run_id.txt
#   RUN_ID=abc123 bash 03-monitor-run.sh             # explicit run-id
#   INTERVAL=30 MAX_POLLS=200 bash 03-monitor-run.sh # custom polling

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"

ENV="${ENV:-$(cat "${ARTIFACTS_DIR}/last_env.txt" 2>/dev/null || echo staging)}"
RUN_ID="${RUN_ID:-$(cat "${ARTIFACTS_DIR}/last_run_id.txt" 2>/dev/null || true)}"
INTERVAL="${INTERVAL:-15}"
MAX_POLLS="${MAX_POLLS:-200}"  # 200 polls × 15s = 50 min default

cyan()  { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
yel()   { printf "\033[33m%s\033[0m\n" "$*"; }

if [[ -z "${RUN_ID}" ]]; then
  red "❌ No run-id available. Pass RUN_ID=... or run 02-submit-job.sh first."
  exit 1
fi

cyan "============================================================"
cyan " ML Studio Run Monitor"
cyan "============================================================"
echo "Run ID  : ${RUN_ID}"
echo "Env     : ${ENV}"
echo "Interval: ${INTERVAL}s"
echo "Max poll: ${MAX_POLLS}"
echo

TERMINAL_RE='^(SUCCEEDED|COMPLETED|SUCCESS|FAILED|CANCELLED|CANCELED|TIMED_OUT|TIMEOUT|ERROR)$'

LAST_STATUS=""
for ((i=1; i<=MAX_POLLS; i++)); do
  TS="$(date '+%H:%M:%S')"
  # NOTE: -w expects ML Studio workflow run UUID; -r expects Databricks run id (≤30 chars)
  # --simple returns: { "status": "RUNNING" }   (or RUNNING/SUCCEEDED/FAILED/...)
  RAW="$(atlas ml workflow run-status -e "${ENV}" -w "${RUN_ID}" --region us --simple 2>&1 || true)"
  CLEAN="$(echo "${RAW}" | grep -v 'ExperimentalWarning\|trace-warnings' || true)"

  # Extract from { "status": "..." } or { "overallStatus": "..." }
  STATUS="$(echo "${CLEAN}" | grep -oE '"(overallStatus|status|state|run_?[Ss]tatus)"\s*:\s*"[^"]+"' | head -1 | sed -E 's/.*"([A-Za-z_]+)"$/\1/' || true)"
  if [[ -z "${STATUS}" ]]; then
    STATUS="$(echo "${CLEAN}" | grep -oE '\b(RUNNING|PENDING|QUEUED|SUCCEEDED|COMPLETED|SUCCESS|FAILED|CANCELLED|CANCELED|TIMED_OUT|TIMEOUT|ERROR)\b' | head -1 || true)"
  fi
  STATUS="${STATUS:-UNKNOWN}"

  if [[ "${STATUS}" != "${LAST_STATUS}" ]]; then
    case "${STATUS}" in
      SUCCEEDED|COMPLETED|SUCCESS) green "[${TS}] ${STATUS}" ;;
      FAILED|CANCELLED|CANCELED|TIMED_OUT|TIMEOUT|ERROR) red "[${TS}] ${STATUS}" ;;
      *) yel "[${TS}] ${STATUS}" ;;
    esac
    LAST_STATUS="${STATUS}"
  else
    printf "."
  fi

  if [[ "${STATUS}" =~ ${TERMINAL_RE} ]]; then
    echo ""
    echo "----- final response -----"
    echo "${CLEAN}"
    echo "--------------------------"
    case "${STATUS}" in
      SUCCEEDED|COMPLETED|SUCCESS)
        green "✓ Run finished successfully"
        echo "Step-level details (with --include-all):"
        echo "  atlas ml workflow run-status -e ${ENV} -w ${RUN_ID} --region us --include-all"
        exit 0
        ;;
      *)
        red "❌ Run terminated with ${STATUS}"
        echo "Step-level details:"
        echo "  atlas ml workflow run-status -e ${ENV} -w ${RUN_ID} --region us --include-all"
        echo "Step logs from Databricks UI: see 'databricksRun' link inside the response."
        exit 4
        ;;
    esac
  fi

  sleep "${INTERVAL}"
done

echo ""
red "⏱  Polling exceeded MAX_POLLS=${MAX_POLLS} (${STATUS}). Job may still be running."
echo "Continue manually:"
echo "  atlas ml workflow run-status -e ${ENV} -r ${RUN_ID}"
exit 5
