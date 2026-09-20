#!/usr/bin/env bash
# PR-2 / HF-02: structural tests on temporal-pdbs.yaml
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PDBS="${PDBS_FILE:-${HERE}/../temporal-pdbs.yaml}"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
pass=0; fail=0
ok() { echo -e "  ${GREEN}PASS${NC} $1"; pass=$((pass+1)); }
ko() { echo -e "  ${RED}FAIL${NC} $1${2:+ — }${2:-}"; fail=$((fail+1)); }

[[ ! -f "$PDBS" ]] && { echo "FATAL: $PDBS not found"; exit 2; }

# P1: YAML parse, exactly 6 PDB documents
n=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
print(len(docs))
" "$PDBS" 2>&1)
[[ "$n" == "6" ]] && ok "P1: 6 PDB documents" || ko "P1: expected 6 docs, got $n"

# P2: all kind=PodDisruptionBudget, apiVersion=policy/v1
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
bad = [(d.get('metadata',{}).get('name'), d.get('kind'), d.get('apiVersion')) for d in docs if d.get('kind') != 'PodDisruptionBudget' or d.get('apiVersion') != 'policy/v1']
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P2: all kind=PodDisruptionBudget, apiVersion=policy/v1" || ko "P2: $res"

# P3: all in temporal namespace
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
bad = [d.get('metadata',{}).get('name') for d in docs if d.get('metadata',{}).get('namespace') != 'temporal']
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P3: all in 'temporal' namespace" || ko "P3: $res"

# P4: all use minAvailable: 1
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
bad = [d['metadata']['name'] for d in docs if d.get('spec',{}).get('minAvailable') != 1]
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P4: all minAvailable: 1" || ko "P4: $res"

# P5: selector includes name + instance + component
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
required = {'app.kubernetes.io/name', 'app.kubernetes.io/instance', 'app.kubernetes.io/component'}
bad = []
for d in docs:
  ml = d.get('spec',{}).get('selector',{}).get('matchLabels',{})
  missing = required - set(ml.keys())
  if missing: bad.append((d['metadata']['name'], list(missing)))
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P5: selectors have name+instance+component" || ko "P5: $res"

# P6: all carry helmfile-enhancement-plan/closes: HF-02 label
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
bad = [d['metadata']['name'] for d in docs if d.get('metadata',{}).get('labels',{}).get('helmfile-enhancement-plan/closes') != 'HF-02']
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P6: all have closes: HF-02 label" || ko "P6: $res"

# P7: components cover the 6 expected roles
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
got = set(d['spec']['selector']['matchLabels']['app.kubernetes.io/component'] for d in docs)
want = {'frontend','history','matching','worker','web','replica'}
missing = want - got
extra = got - want
if missing or extra:
  print(f'BAD missing={missing} extra={extra}')
else:
  print('OK')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P7: components cover frontend/history/matching/worker/web/replica" || ko "P7: $res"

# P8: no two PDBs have identical selectors (component disambiguates)
res=$(python3 -c "
import yaml,sys
from collections import Counter
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
sel_keys = [tuple(sorted(d['spec']['selector']['matchLabels'].items())) for d in docs]
dups = [s for s,c in Counter(sel_keys).items() if c > 1]
print('OK' if not dups else f'BAD duplicate selectors: {dups}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P8: no duplicate selectors" || ko "P8: $res"

# P9: maxUnavailable NOT used (mutually exclusive with minAvailable per PDB schema)
res=$(python3 -c "
import yaml,sys
docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
bad = [d['metadata']['name'] for d in docs if 'maxUnavailable' in d.get('spec',{})]
print('OK' if not bad else f'BAD {bad}')
" "$PDBS")
[[ "$res" == "OK" ]] && ok "P9: maxUnavailable not set" || ko "P9: $res"

echo
echo "=== test_pdbs.sh: ${pass} passed, ${fail} failed ==="
[[ "$fail" -eq 0 ]] && exit 0 || exit 1
