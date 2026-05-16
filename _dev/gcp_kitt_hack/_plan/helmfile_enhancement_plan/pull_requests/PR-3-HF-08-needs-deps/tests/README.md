# Tests — HF-08 helmfile `needs:` dependencies

Offline tests for `helmfile/helmfile.yaml` after adding `needs:` declarations.

## Files
- `test_needs.sh` — 10 structural assertions over the modified helmfile.yaml
- `run_all.sh` — orchestrator (returns 0 iff all pass)

## What's tested
1. helmfile.yaml is valid YAML
2. Exactly 6 releases declared (no accidental duplication during edit)
3. `temporal/temporal` release has `needs:` referencing `temporal/temporal-postgresql` and `temporal/temporal-redis`
4. `temporal/temporal-helloworld-worker` needs `temporal/temporal`
5. `temporal/temporal-helloworld-go-web-service` needs `temporal/temporal`
6. `temporal-postgresql` and `temporal-redis` have NO `needs:` (foundational)
7. `s3-crud-api` has NO `needs:` (independent)
8. Every release named in any `needs:` block actually exists in the file (no broken refs)
9. No `needs:` references itself (no self-deps)
10. The `needs:` keys use the canonical `<namespace>/<release>` format

## What's NOT tested (out of scope)
- Whether helmfile actually executes deploys in the right order (requires live cluster)
- Whether the dependent releases are healthy when the dependent starts (covered by HF-01/03/02 PR-2)
- Whether helm chart subcharts have correct version compatibility

## Run
```bash
bash run_all.sh
# expect: OVERALL_RC=0, 10/10 PASS
```
