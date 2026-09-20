#!/usr/bin/env bash
# Logic + edge-case validation for patch.sh, using a mocked `kubectl`.
# Pure bash + python3 + pyyaml. No cluster, no Docker.
#
# Special exit codes:
#   0 = all green
#   1 = unexpected failure (manifest broken, mock broken, etc.)
#   2 = expected-red defects observed (B1 + B2 documented in tests/README.md)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${MANIFEST:-$HERE/../fix-cassandra-gossip-config-job.yaml}"
MOCK_BIN_DIR="$HERE/mocks"
chmod +x "$MOCK_BIN_DIR/kubectl" 2>/dev/null || true

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[0;33m'; NC=$'\033[0m'
pass=0; fail=0; expected_red=0

# Extract patch.sh from the ConfigMap into a temp file once.
SCRIPT="$(mktemp)"
trap 'rm -f "$SCRIPT" "$LOG" 2>/dev/null || true' EXIT
python3 - <<PYEOF >"$SCRIPT"
import yaml, sys
docs = [d for d in yaml.safe_load_all(open("$MANIFEST")) if d]
cm = next(d for d in docs if d["kind"] == "ConfigMap")
sys.stdout.write(cm["data"]["patch.sh"])
PYEOF

LOG="$(mktemp)"

# Test runner
run_test() {
  local name="$1"; shift
  : > "$LOG"
  if "$@"; then
    echo "  ${GREEN}PASS${NC} $name"
    pass=$((pass+1))
  else
    echo "  ${RED}FAIL${NC} $name"
    fail=$((fail+1))
  fi
}

# Variant of run_test for tests that we EXPECT to fail today (B1, B2)
# but want to track. These don't increment fail count, they increment expected_red.
run_test_expected_red() {
  local name="$1"; shift
  : > "$LOG"
  if "$@"; then
    # If a known-defective test passes, that's actually good — defect was fixed
    echo "  ${GREEN}PASS${NC} $name (was expected-red — defect fixed!)"
    pass=$((pass+1))
  else
    echo "  ${YELLOW}EXPECTED-RED${NC} $name (B-id documented in tests/README.md)"
    expected_red=$((expected_red+1))
  fi
}

# Execute patch.sh in a sandbox: PATH points to mocks/, sleep is a no-op, kubectl returns mocked data.
exec_script() {
  # $1 = REPLICAS override; rest are env exports as KEY=VAL
  local replicas="$1"; shift
  # shellcheck disable=SC2086
  PATH="$MOCK_BIN_DIR:$PATH" \
  KUBECTL_LOG="$LOG" \
  KUBECTL_GET_READY="${KUBECTL_GET_READY:-true}" \
  KUBECTL_FAIL_ON="${KUBECTL_FAIL_ON:-}" \
  REPLICAS="$replicas" \
  NAMESPACE="${NAMESPACE:-temporal}" \
  STS_NAME="${STS_NAME:-cassandra}" \
  bash -c "$(printf 'sleep() { :; }\n%s' "$(cat "$SCRIPT")")"
}

# ---------------------------------------------------------------------------
# T-S01: Seed list with REPLICAS=3 -> 3 comma-separated DNS names
# ---------------------------------------------------------------------------
test_s01_seeds_replicas_3() {
  out="$(exec_script 3 2>&1)"
  echo "$out" | grep -q "seeds: cassandra-0.cassandra-headless.temporal.svc.cluster.local,cassandra-1.cassandra-headless.temporal.svc.cluster.local,cassandra-2.cassandra-headless.temporal.svc.cluster.local"
}
run_test "T-S01 Seed list with REPLICAS=3 has 3 comma-separated DNS names" test_s01_seeds_replicas_3

# ---------------------------------------------------------------------------
# T-S02: Seed list with REPLICAS=1 -> single DNS name, no comma
# ---------------------------------------------------------------------------
test_s02_seeds_replicas_1() {
  out="$(exec_script 1 2>&1)"
  seed_line="$(echo "$out" | grep '^\[fix-cassandra-gossip\] seeds:' || true)"
  [[ -n "$seed_line" ]] || return 1
  # Must have exactly one DNS name (zero commas)
  comma_count=$(echo "$seed_line" | tr -cd ',' | wc -c | tr -d ' ')
  [[ "$comma_count" == "0" ]]
}
run_test "T-S02 Seed list with REPLICAS=1 has 1 name (no comma)" test_s02_seeds_replicas_1

# ---------------------------------------------------------------------------
# T-S03: Seed list with REPLICAS=5 -> 5 names + 4 commas + correct ordinals
# ---------------------------------------------------------------------------
test_s03_seeds_replicas_5() {
  out="$(exec_script 5 2>&1)"
  for ord in 0 1 2 3 4; do
    echo "$out" | grep -q "cassandra-${ord}.cassandra-headless" || return 1
  done
  seed_line="$(echo "$out" | grep '^\[fix-cassandra-gossip\] seeds:')"
  comma_count=$(echo "$seed_line" | tr -cd ',' | wc -c | tr -d ' ')
  [[ "$comma_count" == "4" ]]
}
run_test "T-S03 Seed list with REPLICAS=5 has 5 names with ordinals 0-4" test_s03_seeds_replicas_5

# ---------------------------------------------------------------------------
# T-S04: kubectl set env failure -> script exits non-zero (set -e propagates)
# ---------------------------------------------------------------------------
test_s04_set_env_failure_aborts() {
  if KUBECTL_FAIL_ON="set" exec_script 3 >/dev/null 2>&1; then
    return 1   # script succeeded => bug
  fi
  # Verify no `delete pod` was attempted (script aborted before reaching restart loop)
  ! grep -q "^delete|" "$LOG"
}
run_test "T-S04 kubectl set env failure aborts the script (set -e propagates)" test_s04_set_env_failure_aborts

# ---------------------------------------------------------------------------
# T-S05: All 6 expected env vars are set on the StatefulSet
# ---------------------------------------------------------------------------
test_s05_all_env_vars_set() {
  exec_script 3 >/dev/null 2>&1 || return 1
  # The `set env` invocation appears as one line in $LOG with all 6 KEY=VAL pairs
  set_line="$(grep '^set|env|' "$LOG" || true)"
  [[ -n "$set_line" ]] || return 1
  for var in CASSANDRA_SEEDS= MAX_HEAP_SIZE=4G HEAP_NEWSIZE=800M JMX_PORT=7199 LOCAL_JMX=no; do
    echo "$set_line" | grep -q "$var" || return 1
  done
  # JVM_EXTRA_OPTS contains G1GC
  echo "$set_line" | grep -q "JVM_EXTRA_OPTS=.*G1GC" || return 1
}
run_test "T-S05 All 6 expected env vars set on StatefulSet (CASSANDRA_SEEDS, heap, JMX, LOCAL_JMX)" test_s05_all_env_vars_set

# ---------------------------------------------------------------------------
# T-S06: Pods restarted in sequential order (cassandra-0, then -1, then -2)
# ---------------------------------------------------------------------------
test_s06_pod_restart_order() {
  exec_script 3 >/dev/null 2>&1 || return 1
  # Extract delete-pod calls in order; each line in LOG is "verb|args|args|..."
  pod_order=$(grep '^delete|pod|' "$LOG" | sed -E 's/^delete\|pod\|-n\|temporal\|([^|]+)\|.*/\1/')
  expected=$'cassandra-0\ncassandra-1\ncassandra-2'
  [[ "$pod_order" == "$expected" ]]
}
run_test "T-S06 Pods restarted sequentially: cassandra-0 -> 1 -> 2" test_s06_pod_restart_order

# ---------------------------------------------------------------------------
# T-S07: Idempotency — script can run twice without error (second run still patches)
# ---------------------------------------------------------------------------
test_s07_idempotent() {
  exec_script 3 >/dev/null 2>&1 || return 1
  first_log="$(cat "$LOG")"
  : > "$LOG"
  exec_script 3 >/dev/null 2>&1 || return 1
  second_log="$(cat "$LOG")"
  # Both runs should issue the same kubectl set env call
  first_set="$(echo "$first_log" | grep '^set|env|')"
  second_set="$(echo "$second_log" | grep '^set|env|')"
  [[ "$first_set" == "$second_set" ]]
}
run_test "T-S07 Idempotent: 2nd run produces identical kubectl set env call" test_s07_idempotent

# ---------------------------------------------------------------------------
# T-S08: Final summary marker is emitted (operator-grep marker)
# ---------------------------------------------------------------------------
test_s08_done_marker() {
  out="$(exec_script 3 2>&1)"
  echo "$out" | grep -q "^\[fix-cassandra-gossip\] DONE$"
}
run_test "T-S08 Final '[fix-cassandra-gossip] DONE' marker is emitted" test_s08_done_marker

# ---------------------------------------------------------------------------
# T-S09 (EXPECTED-RED, defect B1): REPLICAS=0 should error, currently silent no-op
# ---------------------------------------------------------------------------
test_s09_b1_replicas_zero_should_error() {
  # Defect B1: REPLICAS=0 must be a fatal error.
  # On Alpine/GNU (production):  `seq 0 -1` produces no output -> silent no-op (env inert)
  # On macOS/BSD (dev):           `seq 0 -1` produces "0 -1" -> pushes corrupt seed list
  #                               (e.g. "cassandra-0...,cassandra--1...") to live StatefulSet!
  # Either way, the CORRECT behavior is: validate REPLICAS>=1 at the top and exit 1 if not.
  if ! exec_script 0 >/dev/null 2>&1; then
    return 0  # FIXED: script exited non-zero on REPLICAS=0
  fi
  # Script succeeded. Check for any of the 3 known defect signatures.
  set_line="$(grep '^set|env|' "$LOG" || true)"
  delete_lines="$(grep '^delete|pod|' "$LOG" || true)"

  # Signature A (Alpine/GNU): no env set, no pods restarted -> silent no-op
  if [[ -z "$set_line" && -z "$delete_lines" ]]; then
    return 1
  fi
  # Signature B (Alpine/GNU): env set with empty CASSANDRA_SEEDS
  if echo "$set_line" | grep -qE 'CASSANDRA_SEEDS=\|'; then
    return 1
  fi
  # Signature C (macOS/BSD): corrupt seed list with negative ordinal "cassandra--1"
  if echo "$set_line" | grep -q 'cassandra--1'; then
    return 1
  fi
  # Signature D (macOS/BSD): tries to delete pod with negative ordinal name
  if echo "$delete_lines" | grep -q 'cassandra--1'; then
    return 1
  fi
  return 0
}
run_test_expected_red "T-S09 (B1) REPLICAS=0 should be a fatal error, not silent no-op" test_s09_b1_replicas_zero_should_error

# ---------------------------------------------------------------------------
# T-S10 (EXPECTED-RED, defect B2): wait loop never-ready should be fatal
# ---------------------------------------------------------------------------
test_s10_b2_wait_loop_never_ready_is_fatal() {
  # Make every `kubectl get pod ... ready` return "false" so the wait loop never breaks.
  # Currently the script silently moves to the next pod after 60 attempts. Expected: exit 1.
  if KUBECTL_GET_READY=false exec_script 1 >/dev/null 2>&1; then
    return 1  # Script succeeded despite pod never becoming Ready => B2 confirmed
  else
    return 0  # Script errored => B2 is FIXED
  fi
}
run_test_expected_red "T-S10 (B2) Wait-loop exhaustion (pod never Ready) should be a fatal error" test_s10_b2_wait_loop_never_ready_is_fatal

# ---------------------------------------------------------------------------
echo
total=$((pass + fail + expected_red))
if [[ $fail -gt 0 ]]; then
  echo "${RED}test_patch_sh.sh: $pass passed, $fail FAILED, $expected_red expected-red ($total total)${NC}"
  exit 1
elif [[ $expected_red -gt 0 ]]; then
  echo "${YELLOW}test_patch_sh.sh: $pass passed + $expected_red expected-red = $total total${NC}"
  exit 2
else
  echo "${GREEN}test_patch_sh.sh: $pass/$total PASS${NC}"
  exit 0
fi
