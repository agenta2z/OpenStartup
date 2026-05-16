#!/usr/bin/env bash
# crash_root_cause_diagnostic.sh
# ----------------------------------------------------------------------
# Read-only diagnostic that maps observed runtime evidence to HF findings
# to identify which static defects are the ACTIVE cause of crashes.
#
# Authored: 2026-05-11 by helmfile_enhancement_plan/ Tier-0 work
#
# WHAT THIS DOES:
#   Runs a fixed sequence of read-only kubectl/psql/curl commands and
#   classifies the result for each candidate root cause as:
#     CONFIRMED  — evidence strongly supports this HF as active root cause
#     LIKELY     — evidence consistent with this HF (false-pos possible)
#     UNLIKELY   — evidence inconsistent with this HF
#     INCONCLUSIVE — diagnostic could not determine (false-neg risk)
#
# WHAT THIS DOES NOT DO:
#   - No writes / no patches / no kubectl exec into shells (only read-only commands)
#   - No `helm upgrade` / no `kubectl delete` / no `kubectl apply`
#   - No assumptions about pod label names — discovers labels at runtime
#
# USAGE:
#   bash crash_root_cause_diagnostic.sh              # default (all checks)
#   NAMESPACE=foo bash crash_root_cause_diagnostic.sh
#   HF=HF-54,HF-56 bash crash_root_cause_diagnostic.sh   # subset
#   VERBOSE=1 bash crash_root_cause_diagnostic.sh        # show raw command output
#   JSON=1 bash crash_root_cause_diagnostic.sh           # emit JSON instead of human-readable
#
# REQUIREMENTS:
#   - kubectl with access to target cluster
#   - jq
#   - helm (optional; HF-07 + HF-54-postsync skipped if absent)
#   - curl + bash 4+
#
# EXIT CODES:
#   0   = at least one HF CONFIRMED — actionable root cause(s) found
#   1   = no HF CONFIRMED but ≥1 LIKELY — needs investigation
#   2   = nothing CONFIRMED or LIKELY (cluster looks healthy from these angles)
#   3   = diagnostic itself failed (cluster unreachable, etc.)

set -euo pipefail

# ---------- Configuration ----------
NAMESPACE="${NAMESPACE:-temporal}"
DTE_NAMESPACE="${DTE_NAMESPACE:-${NAMESPACE}}"   # DTE may live in same ns
KEDA_NAMESPACE="${KEDA_NAMESPACE:-keda}"
HELMFILE_DIR="${HELMFILE_DIR:-/Users/tchen7/MyProjects/atlassian_packages/gcp_kitt/helmfile}"
HF_FILTER="${HF:-}"                # empty = run all
VERBOSE="${VERBOSE:-0}"
JSON_OUT="${JSON:-0}"
TIME_WINDOW_MIN="${TIME_WINDOW_MIN:-15}"   # default lookback for restart counts / logs

# ---------- Bookkeeping ----------
declare -A HF_VERDICT          # HF-id => CONFIRMED|LIKELY|UNLIKELY|INCONCLUSIVE
declare -A HF_EVIDENCE         # HF-id => one-line evidence string
declare -A HF_FALSEPOS_NOTE    # HF-id => false-positive caveat
RESULTS_JSON="["
FIRST_JSON=1

CONFIRMED_COUNT=0
LIKELY_COUNT=0

# ---------- Color (only if TTY) ----------
if [[ -t 1 ]] && [[ "${JSON_OUT}" != "1" ]]; then
  RED=$'\033[31m'; YELLOW=$'\033[33m'; GREEN=$'\033[32m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'
else
  RED=""; YELLOW=""; GREEN=""; BOLD=""; DIM=""; NC=""
fi

# ---------- Helpers ----------
should_run() {
  # $1 = HF id; if HF_FILTER is empty, run all; else only run those listed
  if [[ -z "${HF_FILTER}" ]]; then return 0; fi
  [[ ",${HF_FILTER}," == *",$1,"* ]]
}

record() {
  # $1 = HF-id, $2 = verdict, $3 = evidence, $4 = false-pos caveat (optional)
  local id="$1" verdict="$2" evidence="$3" caveat="${4:-}"
  HF_VERDICT["$id"]="$verdict"
  HF_EVIDENCE["$id"]="$evidence"
  HF_FALSEPOS_NOTE["$id"]="$caveat"
  case "$verdict" in
    CONFIRMED) CONFIRMED_COUNT=$((CONFIRMED_COUNT+1)) ;;
    LIKELY)    LIKELY_COUNT=$((LIKELY_COUNT+1)) ;;
  esac
  if [[ "${JSON_OUT}" == "1" ]]; then
    [[ $FIRST_JSON -eq 1 ]] && FIRST_JSON=0 || RESULTS_JSON+=","
    RESULTS_JSON+="$(jq -n --arg id "$id" --arg v "$verdict" --arg e "$evidence" --arg c "$caveat" \
      '{hf:$id,verdict:$v,evidence:$e,false_positive_caveat:$c}')"
  fi
}

vlog() { [[ "${VERBOSE}" == "1" ]] && echo "${DIM}  [debug] $*${NC}" >&2 || true; }

heading() {
  [[ "${JSON_OUT}" == "1" ]] && return 0
  echo
  echo "${BOLD}─── $* ───${NC}"
}

verdict_color() {
  case "$1" in
    CONFIRMED) echo "${RED}${BOLD}$1${NC}" ;;
    LIKELY)    echo "${YELLOW}$1${NC}" ;;
    UNLIKELY)  echo "${GREEN}$1${NC}" ;;
    *)         echo "${DIM}$1${NC}" ;;
  esac
}

# ---------- Pre-flight ----------
heading "Pre-flight"
if ! command -v kubectl >/dev/null; then echo "${RED}ERROR: kubectl not found${NC}"; exit 3; fi
if ! command -v jq >/dev/null; then echo "${RED}ERROR: jq not found${NC}"; exit 3; fi

if ! kubectl get ns "${NAMESPACE}" >/dev/null 2>&1; then
  echo "${RED}ERROR: namespace '${NAMESPACE}' not found. Set NAMESPACE=…${NC}"
  exit 3
fi
[[ "${JSON_OUT}" != "1" ]] && echo "  namespace: ${NAMESPACE}   dte-ns: ${DTE_NAMESPACE}   keda-ns: ${KEDA_NAMESPACE}"

# Discover Temporal pod label at runtime (don't assume app.kubernetes.io/name=temporal)
TEMPORAL_LABEL=""
for cand in "app.kubernetes.io/name=temporal" "app=temporal" "release=temporal"; do
  if [[ -n "$(kubectl get pod -n "${NAMESPACE}" -l "$cand" -o name 2>/dev/null)" ]]; then
    TEMPORAL_LABEL="$cand"; break
  fi
done
[[ -z "$TEMPORAL_LABEL" ]] && TEMPORAL_LABEL="(no Temporal pods found; label discovery failed)"
vlog "TEMPORAL_LABEL=$TEMPORAL_LABEL"

# ---------- HF-54: missing fix-cassandra-gossip-config-job.yaml ----------
if should_run "HF-54"; then
  heading "HF-54  Missing fix-cassandra-gossip-config-job.yaml"
  local_missing=0
  if [[ ! -f "${HELMFILE_DIR}/fix-cassandra-gossip-config-job.yaml" ]]; then
    local_missing=1
  fi

  cassandra_pod="$(kubectl get pod -n "${NAMESPACE}" -l app.kubernetes.io/name=cassandra -o name 2>/dev/null | head -1 || true)"
  [[ -z "$cassandra_pod" ]] && cassandra_pod="$(kubectl get pod -n "${NAMESPACE}" -l app=cassandra -o name 2>/dev/null | head -1 || true)"

  gossip_unhealthy="UNKNOWN"
  if [[ -n "$cassandra_pod" ]]; then
    # nodetool status: count UN (Up Normal) vs total
    if status_out="$(kubectl exec -n "${NAMESPACE}" "${cassandra_pod}" -- nodetool status 2>/dev/null)"; then
      total=$(echo "$status_out" | grep -cE '^[UDS][NLJM] ' || true)
      un=$(echo "$status_out" | grep -cE '^UN ' || true)
      if [[ $total -gt 0 ]]; then
        if [[ $un -lt $total ]]; then
          gossip_unhealthy="YES (UN=$un / total=$total)"
        else
          gossip_unhealthy="NO (all $total nodes UN)"
        fi
      fi
    fi
  fi

  if [[ $local_missing -eq 1 && "$gossip_unhealthy" == YES* ]]; then
    record "HF-54" "CONFIRMED" "File missing AND gossip state degraded: $gossip_unhealthy" \
      "Cassandra UN<total can also indicate ongoing rolling restart; re-check in 5 min"
  elif [[ $local_missing -eq 1 ]]; then
    record "HF-54" "LIKELY" "Postsync hook target file missing on disk; gossip state: $gossip_unhealthy" \
      "If gossip is healthy now, the missed fix may have been applied via another path"
  else
    record "HF-54" "UNLIKELY" "File present on disk; gossip: $gossip_unhealthy"
  fi
fi

# ---------- HF-01: no startupProbe on Temporal services ----------
if should_run "HF-01"; then
  heading "HF-01  No startupProbe on Temporal services + kubelet-kill evidence"

  pods_json="$(kubectl get pod -n "${NAMESPACE}" -l "${TEMPORAL_LABEL}" -o json 2>/dev/null || echo '{"items":[]}')"
  no_startup=$(echo "$pods_json" | jq '[.items[] | select(.spec.containers[0].startupProbe == null)] | length')
  total_pods=$(echo "$pods_json" | jq '.items | length')
  killed_pods=$(echo "$pods_json" | jq '[.items[] | select(.status.containerStatuses[0]?.lastState.terminated.reason // "" | test("Killed|OOMKilled"))] | length')
  high_restart=$(echo "$pods_json" | jq '[.items[] | select((.status.containerStatuses[0]?.restartCount // 0) > 2)] | length')

  if [[ $total_pods -eq 0 ]]; then
    record "HF-01" "INCONCLUSIVE" "No Temporal pods found via label discovery (${TEMPORAL_LABEL})" \
      "Label discovery may have failed; try VERBOSE=1 and adjust"
  elif [[ $no_startup -gt 0 && $killed_pods -gt 0 ]]; then
    record "HF-01" "CONFIRMED" "$no_startup/$total_pods pods missing startupProbe AND $killed_pods pods recently Killed by kubelet (restartCount>2: $high_restart)" \
      "Killed reason can also mean OOMKilled — check exitCode 137 vs 1"
  elif [[ $no_startup -gt 0 && $high_restart -gt 0 ]]; then
    record "HF-01" "LIKELY" "$no_startup/$total_pods pods missing startupProbe; $high_restart pods have restart count >2" \
      "Restarts may be from app-level errors not probe timing"
  elif [[ $no_startup -gt 0 ]]; then
    record "HF-01" "LIKELY" "$no_startup/$total_pods pods missing startupProbe but no recent kubelet kills" \
      "Structural risk present; may not be the active cause right now"
  else
    record "HF-01" "UNLIKELY" "All Temporal pods have startupProbe configured"
  fi
fi

# ---------- HF-03: replicaCount: 1 for Temporal services ----------
if should_run "HF-03"; then
  heading "HF-03  Single-replica Temporal services"

  workloads_json="$(kubectl get deploy,sts -n "${NAMESPACE}" -o json 2>/dev/null || echo '{"items":[]}')"
  single=$(echo "$workloads_json" | jq '[.items[] | select(.metadata.name | test("frontend|history|matching|worker|web|temporal"; "i")) | select(.spec.replicas == 1) | .metadata.name]')
  single_count=$(echo "$single" | jq 'length')

  recent_evictions=$(kubectl get events -n "${NAMESPACE}" --field-selector reason=Evicted --sort-by=.lastTimestamp 2>/dev/null | grep -c -v '^LAST' || true)

  if [[ $single_count -ge 3 && $recent_evictions -gt 0 ]]; then
    record "HF-03" "CONFIRMED" "$single_count single-replica workloads AND $recent_evictions recent Evicted events in ns" \
      ""
  elif [[ $single_count -ge 3 ]]; then
    record "HF-03" "LIKELY" "$single_count workloads at replica=1 (matches: $(echo "$single" | jq -c '.'))" \
      "No recent evictions — structural risk, not yet active. Will become CONFIRMED on next node drain"
  elif [[ $single_count -gt 0 ]]; then
    record "HF-03" "LIKELY" "$single_count workloads at replica=1 (partial match)" ""
  else
    record "HF-03" "UNLIKELY" "No matching workloads at replica=1"
  fi
fi

# ---------- HF-02: missing PDBs ----------
if should_run "HF-02"; then
  heading "HF-02  Missing PodDisruptionBudgets"

  pdb_count=$(kubectl get pdb -n "${NAMESPACE}" -o json 2>/dev/null | jq '.items | length' 2>/dev/null || echo 0)
  recent_drains=$(kubectl get events -n "${NAMESPACE}" --field-selector reason=DrainNode 2>/dev/null | grep -c -v '^LAST' || true)
  if [[ $pdb_count -eq 0 && $recent_drains -gt 0 ]]; then
    record "HF-02" "CONFIRMED" "0 PDBs in ns AND $recent_drains DrainNode events recently" ""
  elif [[ $pdb_count -eq 0 ]]; then
    record "HF-02" "LIKELY" "0 PDBs in namespace ${NAMESPACE}" \
      "Structural risk; only becomes active during a node drain"
  else
    record "HF-02" "UNLIKELY" "$pdb_count PDB(s) defined in ${NAMESPACE}"
  fi
fi

# ---------- HF-56: PostgreSQL maxConns: 20 (the prime latency suspect) ----------
if should_run "HF-56"; then
  heading "HF-56  PostgreSQL connection-pool exhaustion"

  pg_pod="$(kubectl get pod -n "${NAMESPACE}" -l app.kubernetes.io/name=postgresql -o name 2>/dev/null | head -1 || true)"
  [[ -z "$pg_pod" ]] && pg_pod="$(kubectl get pod -n "${NAMESPACE}" -l app=postgresql -o name 2>/dev/null | head -1 || true)"
  [[ -z "$pg_pod" ]] && pg_pod="$(kubectl get pod -n "${NAMESPACE}" -o name 2>/dev/null | grep -E 'postgres|temporal-postgresql' | head -1 || true)"

  if [[ -z "$pg_pod" ]]; then
    record "HF-56" "INCONCLUSIVE" "No Postgres pod found in ${NAMESPACE}" \
      "Set POSTGRES_POD env or check namespace"
  else
    # 5-minute window: sample pg_stat_activity 10 times at 30s intervals to capture bursts
    # but for a snapshot diagnostic, we do 5 samples at 5s intervals
    max_conns="$(kubectl exec -n "${NAMESPACE}" "${pg_pod}" -- psql -U postgres -tAc "SELECT current_setting('max_connections')::int" 2>/dev/null || echo "?")"
    samples=""
    peak_active=0
    for i in 1 2 3 4 5; do
      cur="$(kubectl exec -n "${NAMESPACE}" "${pg_pod}" -- psql -U postgres -tAc \
        "SELECT count(*) FROM pg_stat_activity WHERE state IN ('active','idle in transaction')" 2>/dev/null || echo 0)"
      samples+="$cur "
      [[ $cur -gt $peak_active ]] && peak_active=$cur
      sleep 5
    done

    too_many_errors="$(kubectl logs -n "${NAMESPACE}" "${pg_pod}" --since="${TIME_WINDOW_MIN}m" 2>/dev/null | grep -ciE 'too many connections|FATAL.*connection' || true)"

    util_pct=$(( peak_active * 100 / max_conns ))
    if [[ $too_many_errors -gt 0 ]]; then
      record "HF-56" "CONFIRMED" "$too_many_errors 'too many connections' errors in last ${TIME_WINDOW_MIN}min; max_conn=$max_conns; peak active+itx=$peak_active (samples: $samples; util=$util_pct%)" ""
    elif [[ $util_pct -ge 80 ]]; then
      record "HF-56" "CONFIRMED" "Peak utilization $util_pct% of max_connections=$max_conns (samples: $samples)" ""
    elif [[ $util_pct -ge 50 ]]; then
      record "HF-56" "LIKELY" "Peak utilization $util_pct% of max=$max_conns (samples: $samples)" \
        "Bursts may exceed during traffic spikes not captured in 30s window"
    elif [[ $max_conns -le 30 ]]; then
      record "HF-56" "LIKELY" "max_connections=$max_conns is dangerously low; current peak=$peak_active (samples: $samples)" \
        "Pool may exhaust under future load even if currently quiet"
    else
      record "HF-56" "UNLIKELY" "max_connections=$max_conns; peak active+itx=$peak_active (util=$util_pct%)"
    fi
  fi
fi

# ---------- HF-58: Elasticsearch yellow + visibility replicas=1 ----------
if should_run "HF-58"; then
  heading "HF-58  Elasticsearch visibility replicas=1 → permanent yellow"

  es_pod="$(kubectl get pod -n "${NAMESPACE}" -l app=elasticsearch-master -o name 2>/dev/null | head -1 || true)"
  [[ -z "$es_pod" ]] && es_pod="$(kubectl get pod -n "${NAMESPACE}" -o name 2>/dev/null | grep -E 'elasticsearch|^pod/es-' | head -1 || true)"

  if [[ -z "$es_pod" ]]; then
    record "HF-58" "INCONCLUSIVE" "No Elasticsearch pod found in ${NAMESPACE}" ""
  else
    health="$(kubectl exec -n "${NAMESPACE}" "${es_pod}" -- curl -s localhost:9200/_cluster/health 2>/dev/null || echo '{}')"
    status=$(echo "$health" | jq -r '.status // "unknown"')
    unassigned=$(echo "$health" | jq -r '.unassigned_shards // 0')
    node_count=$(echo "$health" | jq -r '.number_of_nodes // 0')

    if [[ "$status" == "red" ]]; then
      record "HF-58" "CONFIRMED" "ES status=red, unassigned=$unassigned, nodes=$node_count" ""
    elif [[ "$status" == "yellow" && $unassigned -gt 0 ]]; then
      record "HF-58" "CONFIRMED" "ES status=yellow with $unassigned unassigned shards on $node_count node(s)" \
        "Yellow + replicas=1 + 1 node is structurally inevitable; expected if replicas not set to 0"
    elif [[ "$status" == "green" ]]; then
      record "HF-58" "UNLIKELY" "ES status=green; unassigned=$unassigned; nodes=$node_count"
    else
      record "HF-58" "INCONCLUSIVE" "ES health query returned status=$status (raw response truncated)" ""
    fi
  fi
fi

# ---------- HF-50: os.Setenv race in DTE worker ----------
if should_run "HF-50"; then
  heading "HF-50  DTE worker os.Setenv race (intermittent 401/403)"

  dte_pods="$(kubectl get pod -n "${DTE_NAMESPACE}" -l app=dte-worker -o name 2>/dev/null || true)"
  [[ -z "$dte_pods" ]] && dte_pods="$(kubectl get pod -n "${DTE_NAMESPACE}" -o name 2>/dev/null | grep -E 'dte-?(worker|distributed-worker)' | head -3 || true)"

  if [[ -z "$dte_pods" ]]; then
    record "HF-50" "INCONCLUSIVE" "No DTE worker pods found in ${DTE_NAMESPACE}" ""
  else
    auth_errors=0
    refresh_events=0
    for p in $dte_pods; do
      ae="$(kubectl logs -n "${DTE_NAMESPACE}" "$p" --since="${TIME_WINDOW_MIN}m" 2>/dev/null | grep -cE '401|403|"Unauthorized"|"Forbidden"|permission denied' || true)"
      re="$(kubectl logs -n "${DTE_NAMESPACE}" "$p" --since="${TIME_WINDOW_MIN}m" 2>/dev/null | grep -ciE 'token.refresh|refreshing.*token|new token' || true)"
      auth_errors=$((auth_errors + ae))
      refresh_events=$((refresh_events + re))
    done
    # Heuristic: race is suspected when 401/403 occur WITHOUT proportional refresh activity
    if [[ $auth_errors -gt 5 && $refresh_events -lt $((auth_errors / 5)) ]]; then
      record "HF-50" "LIKELY" "$auth_errors auth errors in ${TIME_WINDOW_MIN}min with only $refresh_events token-refresh events (anomalous ratio)" \
        "Race only manifests at high concurrency; baseline with load test for higher confidence"
    elif [[ $auth_errors -gt 0 ]]; then
      record "HF-50" "LIKELY" "$auth_errors auth errors in ${TIME_WINDOW_MIN}min ($refresh_events refreshes)" \
        "Errors may be from token-expiry, not race"
    else
      record "HF-50" "UNLIKELY" "0 auth errors in last ${TIME_WINDOW_MIN}min" \
        "Race only manifests under concurrency; quiet-period diagnostic cannot exclude"
    fi
  fi
fi

# ---------- HF-27/51/53: DTE worker contract bundle ----------
if should_run "HF-27" || should_run "HF-51" || should_run "HF-53"; then
  heading "HF-27/51/53  DTE worker contract (os.Exit + HTTP timeouts + fake /health)"

  dte_pods_json="$(kubectl get pod -n "${DTE_NAMESPACE}" -l app=dte-worker -o json 2>/dev/null || echo '{"items":[]}')"
  dte_count=$(echo "$dte_pods_json" | jq '.items | length')
  if [[ $dte_count -eq 0 ]]; then
    dte_pods_json="$(kubectl get pod -n "${DTE_NAMESPACE}" -o json 2>/dev/null | jq '{items: [.items[] | select(.metadata.name | test("dte|distributed-worker"))]}')"
    dte_count=$(echo "$dte_pods_json" | jq '.items | length')
  fi

  if [[ $dte_count -eq 0 ]]; then
    record "HF-27" "INCONCLUSIVE" "No DTE worker pods found" ""
  else
    high_restarts=$(echo "$dte_pods_json" | jq '[.items[] | select((.status.containerStatuses[0]?.restartCount // 0) > 1)] | length')
    error_exits=$(echo "$dte_pods_json" | jq '[.items[] | select(.status.containerStatuses[0]?.lastState.terminated.exitCode == 1)] | length')
    oom_exits=$(echo "$dte_pods_json" | jq '[.items[] | select(.status.containerStatuses[0]?.lastState.terminated.reason == "OOMKilled")] | length')

    if [[ $error_exits -gt 0 ]]; then
      record "HF-27" "CONFIRMED" "$error_exits DTE pod(s) with lastState.exitCode=1 (matches os.Exit(1) signature); restartCount>1: $high_restarts" \
        "exitCode=1 can also be other panics; check pod logs for 'panic:' or 'os.Exit'"
    elif [[ $oom_exits -gt 0 ]]; then
      record "HF-27" "UNLIKELY" "$oom_exits DTE pod(s) OOMKilled — distinct from os.Exit; investigate memory limits" ""
    elif [[ $high_restarts -gt 0 ]]; then
      record "HF-27" "LIKELY" "$high_restarts DTE pod(s) with restartCount>1; cause unclear from k8s state" \
        "Could be HF-27 os.Exit, or unrelated; correlate with pod logs"
    else
      record "HF-27" "UNLIKELY" "DTE pods stable (no recent restarts)" \
        "HF-27 may be dormant under low load; structural risk remains"
    fi
  fi
fi

# ---------- HF-07: dual Temporal backend config drift ----------
if should_run "HF-07"; then
  heading "HF-07  Dual Temporal backend config (Cassandra ↔ Postgres drift)"

  if command -v helm >/dev/null; then
    values="$(helm get values temporal -n "${NAMESPACE}" -o json 2>/dev/null || echo '{}')"
    has_cass=$(echo "$values" | jq -r '.. | objects | select(has("driver")) | .driver // empty' | grep -ci cassandra || true)
    has_pg=$(echo "$values" | jq -r '.. | objects | select(has("driver")) | .driver // empty' | grep -ci postgres || true)

    if [[ $has_cass -gt 0 && $has_pg -gt 0 ]]; then
      record "HF-07" "CONFIRMED" "Live release has BOTH cassandra AND postgres driver references" ""
    elif [[ $has_cass -gt 0 || $has_pg -gt 0 ]]; then
      drv=$([[ $has_cass -gt 0 ]] && echo cassandra || echo postgres)
      record "HF-07" "UNLIKELY" "Live release uses only $drv driver (no dual config currently active)" \
        "temporal-values.yaml on disk still declares the OTHER backend; armed-bomb risk if applied"
    else
      record "HF-07" "INCONCLUSIVE" "Could not parse driver from helm values" ""
    fi
  else
    record "HF-07" "INCONCLUSIVE" "helm CLI not available; cannot inspect live release values" ""
  fi
fi

# ---------- HF-10: KEDA cannot reach gRPC frontend ----------
if should_run "HF-10"; then
  heading "HF-10  KEDA Temporal scaler gRPC failure"

  so_count=$(kubectl get scaledobject -n "${NAMESPACE}" --no-headers 2>/dev/null | wc -l | tr -d ' ' || true)
  if [[ "$so_count" == "0" || -z "$so_count" ]]; then
    record "HF-10" "INCONCLUSIVE" "No ScaledObject in ${NAMESPACE} — KEDA may not be installed or not configured" ""
  else
    # Check HPA — if KEDA is failing to fetch metric, currentReplicas stays at min and condition has FailedGetExternalMetric
    hpa_failed=$(kubectl get hpa -n "${NAMESPACE}" -o json 2>/dev/null \
      | jq '[.items[] | .status.conditions[]? | select(.type=="ScalingActive" and .status=="False")] | length')
    keda_errors=$(kubectl logs -n "${KEDA_NAMESPACE}" deployment/keda-operator --since="${TIME_WINDOW_MIN}m" 2>/dev/null \
      | grep -ciE 'temporal.*error|temporal.*failed|grpc.*temporal.*(refused|timeout|unavailable)' || true)

    if [[ $hpa_failed -gt 0 && $keda_errors -gt 0 ]]; then
      record "HF-10" "CONFIRMED" "$hpa_failed HPA(s) with ScalingActive=False AND $keda_errors KEDA errors mentioning Temporal in last ${TIME_WINDOW_MIN}min" ""
    elif [[ $hpa_failed -gt 0 ]]; then
      record "HF-10" "LIKELY" "$hpa_failed HPA(s) inactive; KEDA logs not conclusive" ""
    elif [[ $keda_errors -gt 0 ]]; then
      record "HF-10" "LIKELY" "$keda_errors KEDA error(s) about Temporal in last ${TIME_WINDOW_MIN}min" \
        "May be transient; check if errors cluster"
    else
      record "HF-10" "UNLIKELY" "No HPA failures + no KEDA errors about Temporal" ""
    fi
  fi
fi

# ---------- Summary ----------
heading "Summary"

if [[ "${JSON_OUT}" == "1" ]]; then
  RESULTS_JSON+="]"
  echo "$RESULTS_JSON" | jq .
else
  printf "  %-12s  %-14s  %s\n" "HF" "Verdict" "Evidence"
  printf "  %-12s  %-14s  %s\n" "----" "-------" "--------"
  for hf in HF-54 HF-01 HF-03 HF-02 HF-56 HF-58 HF-50 HF-27 HF-07 HF-10; do
    if [[ -n "${HF_VERDICT[$hf]:-}" ]]; then
      v="$(verdict_color "${HF_VERDICT[$hf]}")"
      printf "  %-12s  %-25s  %s\n" "$hf" "$v" "${HF_EVIDENCE[$hf]}"
      [[ -n "${HF_FALSEPOS_NOTE[$hf]:-}" ]] && printf "  %-12s  %-14s  ${DIM}caveat:${NC} %s\n" "" "" "${HF_FALSEPOS_NOTE[$hf]}"
    fi
  done

  echo
  echo "  ${BOLD}CONFIRMED:${NC} ${RED}${CONFIRMED_COUNT}${NC}    ${BOLD}LIKELY:${NC} ${YELLOW}${LIKELY_COUNT}${NC}"
  echo
  if [[ $CONFIRMED_COUNT -gt 0 ]]; then
    echo "  ${BOLD}Action:${NC} ship the CONFIRMED items first; see helmfile_enhancement_plan/04_PR_BREAKDOWN.md"
  elif [[ $LIKELY_COUNT -gt 0 ]]; then
    echo "  ${BOLD}Action:${NC} re-run during traffic peak; LIKELY items may be dormant under low load"
  else
    echo "  ${BOLD}Action:${NC} cluster healthy from these angles; investigate other HF or non-helmfile causes"
  fi
fi

# ---------- Exit code ----------
if [[ $CONFIRMED_COUNT -gt 0 ]]; then exit 0
elif [[ $LIKELY_COUNT -gt 0 ]]; then exit 1
else exit 2; fi
