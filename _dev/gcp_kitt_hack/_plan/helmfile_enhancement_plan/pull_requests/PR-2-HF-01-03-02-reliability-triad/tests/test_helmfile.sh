#!/usr/bin/env bash
# PR-2 / HF-01+03+02: structural tests on the modified helmfile.yaml
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HELMFILE="${HF_TEST_FILE:-${HERE}/../helmfile.yaml}"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
pass=0; fail=0
ok() { echo -e "  ${GREEN}PASS${NC} $1"; pass=$((pass+1)); }
ko() { echo -e "  ${RED}FAIL${NC} $1${2:+ — }${2:-}"; fail=$((fail+1)); }

[[ ! -f "$HELMFILE" ]] && { echo "FATAL: $HELMFILE not found"; exit 2; }

# Helper: extract the 'temporal' release values block as a python obj
read -r -d '' GET_TEMPORAL <<'PYEOF' || true
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  if not d: continue
  for r in d.get('releases', []):
    if r.get('name') == 'temporal' and r.get('namespace') == 'temporal':
      # Merge values list (helmfile values: is a list of dicts)
      merged = {}
      for v in r.get('values', []):
        if isinstance(v, dict): merged.update(v)
      print(yaml.safe_dump(merged))
      sys.exit(0)
print('NO_RELEASE')
PYEOF

# H1: helmfile.yaml is valid YAML, 6 releases
n=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
print(sum(len(d.get('releases', [])) for d in docs if d))
" "$HELMFILE" 2>&1)
[[ "$n" == "6" ]] && ok "H1: helmfile valid YAML with 6 releases" || ko "H1: expected 6 releases, got $n"

# H2: temporal/temporal has server.replicaCount: 2
res=$(python3 -c "$GET_TEMPORAL" "$HELMFILE" | python3 -c "
import yaml,sys
v = yaml.safe_load(sys.stdin)
sr = v.get('server', {}).get('replicaCount')
print('OK' if sr == 2 else f'BAD server.replicaCount={sr}')
")
[[ "$res" == "OK" ]] && ok "H2: server.replicaCount: 2 (HF-03)" || ko "H2: $res"

# H3: temporal-redis has replica.replicaCount: 2
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r.get('name') == 'temporal-redis':
      merged = {}
      for v in r.get('values', []):
        if isinstance(v, dict): merged.update(v)
      rc = merged.get('replica', {}).get('replicaCount')
      print('OK' if rc == 2 else f'BAD replica.replicaCount={rc}')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "H3: redis replica.replicaCount: 2 (HF-03 redis)" || ko "H3: $res"

# H4: temporal/temporal has web.replicaCount: 2
res=$(python3 -c "$GET_TEMPORAL" "$HELMFILE" | python3 -c "
import yaml,sys
v = yaml.safe_load(sys.stdin)
wr = v.get('web', {}).get('replicaCount')
print('OK' if wr == 2 else f'BAD web.replicaCount={wr}')
")
[[ "$res" == "OK" ]] && ok "H4: web.replicaCount: 2 (HF-03 web)" || ko "H4: $res"

# H5: server.frontend.startupProbe exists with failureThreshold >= 30
res=$(python3 -c "$GET_TEMPORAL" "$HELMFILE" | python3 -c "
import yaml,sys
v = yaml.safe_load(sys.stdin)
sp = v.get('server', {}).get('frontend', {}).get('startupProbe', {})
ft = sp.get('failureThreshold', 0)
print('OK' if ft >= 30 else f'BAD frontend.startupProbe.failureThreshold={ft}')
")
[[ "$res" == "OK" ]] && ok "H5: frontend.startupProbe.failureThreshold>=30 (HF-01)" || ko "H5: $res"

# H6: all 4 server roles have startupProbe
res=$(python3 -c "$GET_TEMPORAL" "$HELMFILE" | python3 -c "
import yaml,sys
v = yaml.safe_load(sys.stdin)
srv = v.get('server', {})
missing = [r for r in ('frontend','history','matching','worker') if not srv.get(r, {}).get('startupProbe')]
print('OK' if not missing else f'BAD missing startupProbe for: {missing}')
")
[[ "$res" == "OK" ]] && ok "H6: all 4 server roles have startupProbe (HF-01)" || ko "H6: $res"

# H7: postsync hook for temporal-pdbs.yaml exists
res=$(python3 -c "
import yaml,sys
docs = list(yaml.safe_load_all(open(sys.argv[1])))
for d in docs:
  for r in d.get('releases', []):
    if r.get('name') == 'temporal' and r.get('namespace') == 'temporal':
      hooks = r.get('hooks', [])
      pdb_hooks = [h for h in hooks if 'temporal-pdbs.yaml' in str(h.get('args', []))]
      print('OK' if pdb_hooks else f'BAD no temporal-pdbs.yaml hook found in {len(hooks)} hooks')
      sys.exit(0)
print('NO_RELEASE')
" "$HELMFILE")
[[ "$res" == "OK" ]] && ok "H7: temporal-pdbs.yaml postsync hook wired (HF-02)" || ko "H7: $res"

# H8: All 4 roles have liveness, readiness, startup probes (full triad)
res=$(python3 -c "$GET_TEMPORAL" "$HELMFILE" | python3 -c "
import yaml,sys
v = yaml.safe_load(sys.stdin)
srv = v.get('server', {})
needed = ('startupProbe','livenessProbe','readinessProbe')
missing = []
for role in ('frontend','history','matching','worker'):
  for p in needed:
    if not srv.get(role, {}).get(p):
      missing.append(f'{role}.{p}')
print('OK' if not missing else f'BAD missing: {missing}')
")
[[ "$res" == "OK" ]] && ok "H8: all 4 roles have full probe triad (start/live/ready)" || ko "H8: $res"

echo
echo "=== test_helmfile.sh: ${pass} passed, ${fail} failed ==="
[[ "$fail" -eq 0 ]] && exit 0 || exit 1
