#!/usr/bin/env bash
# PR-2 reliability triad: test orchestrator
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "==> PR-2 (HF-01+02+03) tests"
fail=0
shopt -s nullglob
tests=( "$DIR"/test_*.sh )
shopt -u nullglob
if [[ "${#tests[@]}" -eq 0 ]]; then echo "No tests found in $DIR"; exit 2; fi
for t in "${tests[@]}"; do
  echo "--- $(basename "$t") ---"
  if ! bash "$t"; then fail=$((fail+1)); fi
done
if [[ "$fail" -eq 0 ]]; then echo "==> OVERALL_RC=0 (all suites passed)"; exit 0
else echo "==> OVERALL_RC=1 ($fail suite(s) failed)"; exit 1; fi
