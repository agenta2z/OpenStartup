#!/usr/bin/env bash
# test_pr1.sh — local validation for PR-1 (HF-54 gossip job restoration)
# Runs without cluster access. Validates YAML, schema, bash logic, idempotency.
set -euo pipefail

PR_DIR="$(cd "$(dirname "$0")" && pwd)"
JOB_FILE="$PR_DIR/fix-cassandra-gossip-config-job.yaml"
HELMFILE_YAML="/Users/tchen7/MyProjects/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml"

PASS=0; FAIL=0
green() { echo "  ✅ $*"; PASS=$((PASS+1)); }
red()   { echo "  ❌ $*"; FAIL=$((FAIL+1)); }

echo "=== PR-1 local tests ==="

# Test 1: YAML parses (5 documents)
echo "--- Test 1: YAML syntax + document count ---"
docs=$(python3 -c "import yaml,sys; print(len(list(yaml.safe_load_all(open('$JOB_FILE')))))" 2>&1)
if [[ "$docs" == "5" ]]; then green "5 valid YAML documents"; else red "expected 5 docs, got: $docs"; fi

# Test 2: kind sanity (one of each expected type)
echo "--- Test 2: expected resource kinds present ---"
kinds=$(python3 -c "
import yaml
for d in yaml.safe_load_all(open('$JOB_FILE')):
    if d: print(d['kind'])
" | sort)
expected=$(echo -e "ConfigMap\nJob\nRole\nRoleBinding\nServiceAccount" | sort)
if [[ "$kinds" == "$expected" ]]; then green "kinds match expected: SA + Role + RoleBinding + ConfigMap + Job"; else red "kinds mismatch:\n  got: $kinds\n  expected: $expected"; fi

# Test 3: structural validity check using Python instead of kubectl (offline-safe)
echo "--- Test 3: required schema fields present (offline structural check) ---"
struct_ok=$(python3 << PYEOF
import yaml, sys
required = {
    'ServiceAccount': ['metadata.name', 'metadata.namespace'],
    'Role':           ['metadata.name', 'metadata.namespace', 'rules'],
    'RoleBinding':    ['metadata.name', 'roleRef.name', 'subjects'],
    'ConfigMap':      ['metadata.name', 'data'],
    'Job':            ['metadata.name', 'spec.template.spec.containers',
                       'spec.ttlSecondsAfterFinished', 'spec.backoffLimit',
                       'spec.activeDeadlineSeconds', 'spec.template.spec.serviceAccountName'],
}
def get(d, dotted):
    cur=d
    for k in dotted.split('.'):
        if cur is None: return None
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur
errors=[]
for doc in yaml.safe_load_all(open('$JOB_FILE')):
    if not doc: continue
    kind = doc.get('kind')
    for path in required.get(kind, []):
        if get(doc, path) in (None, '', []):
            errors.append(f"{kind}: missing {path}")
# Job-specific: image must be pinned (not :latest), securityContext must be set
job = next((d for d in yaml.safe_load_all(open('$JOB_FILE')) if d and d.get('kind')=='Job'), None)
img = get(job, 'spec.template.spec.containers')[0]['image']
if img.endswith(':latest') or ':' not in img:
    errors.append(f"Job container image not pinned: {img}")
sc = get(job, 'spec.template.spec.containers')[0].get('securityContext', {})
if not sc.get('runAsNonRoot'):  errors.append("Job container missing runAsNonRoot")
if not sc.get('readOnlyRootFilesystem'):  errors.append("Job container missing readOnlyRootFilesystem")
if 'ALL' not in (sc.get('capabilities',{}).get('drop') or []):
    errors.append("Job container missing capabilities.drop=[ALL]")
print("OK" if not errors else "ERRORS: " + "; ".join(errors))
PYEOF
)
if [[ "$struct_ok" == "OK" ]]; then
  green "all required schema fields present + image pinned + securityContext hardened"
else
  red "$struct_ok"
fi

# Test 4: extract bash script, validate syntax
echo "--- Test 4: embedded patch.sh syntax ---"
script_tmp="$(mktemp)"
python3 -c "
import yaml
for d in yaml.safe_load_all(open('$JOB_FILE')):
    if d and d.get('kind')=='ConfigMap':
        with open('$script_tmp','w') as f:
            f.write(d['data']['patch.sh'])
        break
"
if bash -n "$script_tmp" 2>/dev/null; then
  green "patch.sh passes bash -n syntax check"
else
  red "patch.sh syntax error: $(bash -n "$script_tmp" 2>&1)"
fi

# Test 5: idempotency check via mock kubectl
echo "--- Test 5: idempotency (mock kubectl) ---"
mock_dir="$(mktemp -d)"
cat > "$mock_dir/kubectl" <<'MOCK'
#!/usr/bin/env bash
# mock that returns BOTH desired flags as already-set
case "$*" in
  *"get statefulset temporal-cassandra"*) echo "fake-sts-exists" ;;
  *"jsonpath"*"CASSANDRA_EXTRA_JVM_OPTS"*) echo "-Dfoo=1 -Dcassandra.consistent.rangemovement=false -Dcassandra.load_ring_state=false" ;;
  *"jsonpath="*".spec.replicas"*) echo "3" ;;
  *) exit 0 ;;
esac
MOCK
chmod +x "$mock_dir/kubectl"
out=$(PATH="$mock_dir:$PATH" bash "$script_tmp" 2>&1 || true)
if echo "$out" | grep -q "nothing to do"; then
  green "idempotency OK: script exits early when both flags already present"
else
  red "idempotency failed; output:\n$(echo "$out" | head -5)"
fi
rm -rf "$mock_dir"

# Test 6: append-not-overwrite check via mock kubectl
echo "--- Test 6: append-not-overwrite (mock kubectl) ---"
mock_dir="$(mktemp -d)"
cat > "$mock_dir/kubectl" <<'MOCK'
#!/usr/bin/env bash
# mock that returns ONLY ONE of the two desired flags + existing custom flag
case "$*" in
  *"get statefulset temporal-cassandra"*) echo "fake-sts-exists" ;;
  *"jsonpath"*"CASSANDRA_EXTRA_JVM_OPTS"*) echo "-Dexisting=value -Dcassandra.load_ring_state=false" ;;
  *"jsonpath="*".spec.replicas"*) echo "1" ;;
  *"patch statefulset"*) echo "PATCH_INVOKED: $*" >&2 ;;
  *"delete pod"*) ;;
  *"wait"*) ;;
  *"exec"*) ;;
  *) ;;
esac
MOCK
chmod +x "$mock_dir/kubectl"
err_log="$(mktemp)"
out=$(PATH="$mock_dir:$PATH" bash "$script_tmp" 2>"$err_log" || true)
patch_line=$(grep -E 'PATCH_INVOKED' "$err_log" || true)
new_value=$(echo "$out" | grep -E '^==> Patching to:' | sed 's/^==> Patching to: //')
if echo "$new_value" | grep -q -- "-Dexisting=value" \
   && echo "$new_value" | grep -q -- "-Dcassandra.load_ring_state=false" \
   && echo "$new_value" | grep -q -- "-Dcassandra.consistent.rangemovement=false"; then
  green "append-not-overwrite OK: existing flag preserved + missing flag added"
else
  red "append failed; computed value: '$new_value'"
fi
rm -rf "$mock_dir" "$err_log"

# Test 7: helmfile.yaml hook reference is preserved
echo "--- Test 7: helmfile.yaml still references the file ---"
if [[ -f "$HELMFILE_YAML" ]]; then
  refs=$(grep -c 'fix-cassandra-gossip-config-job.yaml' "$HELMFILE_YAML" || true)
  if [[ "$refs" -ge 1 ]]; then
    green "helmfile.yaml references the file ($refs occurrences) — postsync hook will find it"
  else
    red "helmfile.yaml has no reference to the file (would mean PR is no-op)"
  fi
else
  echo "  ⚠ skip: helmfile.yaml not present at $HELMFILE_YAML"
fi

rm -f "$script_tmp"
echo
echo "=== PR-1 results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
