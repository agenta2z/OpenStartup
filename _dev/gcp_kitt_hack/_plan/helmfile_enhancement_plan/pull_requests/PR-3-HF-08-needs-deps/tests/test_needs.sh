#!/usr/bin/env bash
# HF-08 needs: structural tests on helmfile.yaml
# Tests run on the modified helmfile.yaml (artifact at ../helmfile.yaml)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HELMFILE="${HF_TEST_FILE:-${HERE}/../helmfile.yaml}"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
pass=0; fail=0
ok()  { echo -e "  ${GREEN}PASS${NC} $1"; pass=$((pass+1)); }
ko()  { echo -e "  ${RED}FAIL${NC} $1${2:+ — }${2:-}"; fail=$((fail+1)); }

if [[ ! -f "$HELMFILE" ]]; then echo "FATAL: $HELMFILE not found"; exit 2; fi

# T1: YAML parse
out=$(python3 -c "import yaml,sys; list(yaml.safe_load_all(open(sys.argv[1])))" "$HELMFILE" 2>&1)
[[ -z "$out" ]] && ok "T1: helmfile.yaml is valid YAML" || ko "T1: yaml parse" "$out"

# T2: exactly 6 releases declared
n_releases=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
n = sum(len(d.get('releases', [])) for d in docs if d)
print(n)
" "$HELMFILE")
[[ "$n_releases" == "6" ]] && ok "T2: exactly 6 releases declared" || ko "T2: expected 6 releases, got $n_releases"

# T3: temporal/temporal has needs: [temporal-postgresql, temporal-redis]
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r['name'] == 'temporal' and r.get('namespace') == 'temporal':
      needs = r.get('needs', [])
      ok = 'temporal/temporal-postgresql' in needs and 'temporal/temporal-redis' in needs
      print('OK' if ok else f'BAD needs={needs}')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T3: temporal needs postgresql + redis" || ko "T3: $res"

# T4: temporal-helloworld-worker needs temporal/temporal
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r['name'] == 'temporal-helloworld-worker':
      needs = r.get('needs', [])
      print('OK' if 'temporal/temporal' in needs else f'BAD needs={needs}')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T4: helloworld-worker needs temporal" || ko "T4: $res"

# T5: temporal-helloworld-go-web-service needs temporal/temporal
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r['name'] == 'temporal-helloworld-go-web-service':
      needs = r.get('needs', [])
      print('OK' if 'temporal/temporal' in needs else f'BAD needs={needs}')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T5: helloworld-web-service needs temporal" || ko "T5: $res"

# T6: temporal-postgresql + temporal-redis have NO needs (they're foundational)
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
bad = []
for d in docs:
  for r in d.get('releases', []):
    if r['name'] in ('temporal-postgresql','temporal-redis') and r.get('needs'):
      bad.append(r['name'])
print('OK' if not bad else f'BAD foundational releases have needs: {bad}')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T6: postgres+redis are foundational (no needs)" || ko "T6: $res"

# T7: s3-crud-api has NO needs (independent)
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r['name'] == 's3-crud-api':
      print('OK' if not r.get('needs') else f'BAD s3-crud-api has needs={r.get(\"needs\")}')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T7: s3-crud-api is independent" || ko "T7: $res"

# T8: every release named in any needs: actually exists in the file (no broken refs)
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
all_releases = set()
all_needs = set()
for d in docs:
  for r in d.get('releases', []):
    all_releases.add(f\"{r.get('namespace','')}/{r['name']}\")
    for n in r.get('needs', []):
      all_needs.add(n)
missing = all_needs - all_releases
print('OK' if not missing else f'BAD broken refs: {missing}')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T8: no broken needs: refs" || ko "T8: $res"

# T9: no release lists itself in needs:
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
self_refs = []
for d in docs:
  for r in d.get('releases', []):
    self_ref = f\"{r.get('namespace','')}/{r['name']}\"
    if self_ref in r.get('needs', []):
      self_refs.append(r['name'])
print('OK' if not self_refs else f'BAD self-refs: {self_refs}')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T9: no self-referencing needs" || ko "T9: $res"

# T10: all needs entries use canonical namespace/release format
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
bad = []
for d in docs:
  for r in d.get('releases', []):
    for n in r.get('needs', []):
      if '/' not in n:
        bad.append((r['name'], n))
print('OK' if not bad else f'BAD malformed: {bad}')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "T10: needs use canonical ns/name format" || ko "T10: $res"

echo
echo "=== test_needs.sh: ${pass} passed, ${fail} failed ==="
[[ "$fail" -eq 0 ]] && exit 0 || exit 1
