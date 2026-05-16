# Tests — PR-2 reliability triad (HF-01 + HF-02 + HF-03)

Offline tests for `helmfile/temporal-pdbs.yaml` (new file) and `helmfile/helmfile.yaml` (modified replicas + probes + postsync hook).

## Files
- `test_pdbs.sh` — 9 tests on the temporal-pdbs.yaml manifest
- `test_helmfile.sh` — 8 tests on the modified helmfile.yaml
- `run_all.sh` — orchestrator (returns 0 iff all pass)

## Test inventory

### test_pdbs.sh
| ID | Assertion |
|---|---|
| P1 | YAML parses, exactly 6 PDB documents |
| P2 | All docs are `kind: PodDisruptionBudget`, `apiVersion: policy/v1` |
| P3 | All PDBs in `temporal` namespace |
| P4 | All have `minAvailable: 1` (not maxUnavailable) |
| P5 | Selector includes `app.kubernetes.io/name + instance + component` (precision) |
| P6 | Each PDB carries `helmfile-enhancement-plan/closes: HF-02` traceability label |
| P7 | Component values cover frontend, history, matching, worker, web, redis-replica |
| P8 | No two PDBs have identical selectors (would conflict) |
| P9 | maxUnavailable NOT used (mutually exclusive with minAvailable) |

### test_helmfile.sh
| ID | Assertion |
|---|---|
| H1 | helmfile.yaml is valid YAML, 6 releases |
| H2 | `temporal/temporal` release has `server.replicaCount: 2` (HF-03) |
| H3 | `temporal-redis` has `replica.replicaCount: 2` (HF-03 redis) |
| H4 | `temporal/temporal` `web.replicaCount: 2` (HF-03 web) |
| H5 | `server.frontend.startupProbe` exists with `failureThreshold >= 30` (HF-01) |
| H6 | `server.{history,matching,worker}.startupProbe` exist (HF-01 all 4 roles) |
| H7 | postsync hook for `temporal-pdbs.yaml` exists in helmfile.yaml hooks (HF-02 wired) |
| H8 | `replicaCount` = 2 for every role (sanity: no leftover `1` for the protected roles) |

## What's NOT tested (out of scope, requires cluster)
- Whether the chart actually applies the per-role probe values (chart silently drops typos)
- Whether `kubectl drain` actually respects the PDB
- Whether 2 replicas actually distribute across nodes (depends on `topologySpreadConstraints` — separate finding HF-NN)
- Probe semantics on a live pod (would need `kubectl exec` + curl)
- Web is annotated as needing minAvailable=1 with replicaCount=1 (which would be deadlock-prone) — we set replicas=2 simultaneously to avoid this

## Run
```bash
bash run_all.sh
# expect: OVERALL_RC=0, 17/17 PASS
```
